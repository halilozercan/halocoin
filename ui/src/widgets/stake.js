import React, { Component } from 'react';
import {MCardStats} from '../components/card.js';
import {Card, CardActions, CardHeader, CardText, CardTitle} from 'material-ui/Card';
import RaisedButton from 'material-ui/RaisedButton';
import Dialog from 'material-ui/Dialog';
import TextField from 'material-ui/TextField';
import axios from 'axios';
import {
  Table,
  TableBody,
  TableHeader,
  TableHeaderColumn,
  TableRow,
  TableRowColumn,
} from 'material-ui/Table';

class RequiredActionPower extends Component {
  constructor(props) {
    super(props);
  }

  handleOpen = (title) => {
    //this.setState({dialogOpen: true, dialogTitle: title});
  };

  render(){
    console.log('Required');
    console.log(this.props.account);
    if(this.props.account.score <= 0) {
      // Redirect to pool registration
      return (
        <div>
          <CardActions align='right'>
            <CardText>
              Your score is not eligible for Power. You need to deposit 1000 coins in order to apply for Power pool.
            </CardText>
            <RaisedButton label="Deposit" primary={true} onClick={() => {this.handleOpen('Deposit')}} />
          </CardActions>      
        </div>
      );
    }
    else {
      // Modify application
      return (
        <div>
          <CardText>
            You can change your application status at any time. It will take affect when your transaction goes through.
          </CardText>
          <CardActions align='right'>
            <RaisedButton label="Edit Application" primary={true} onClick={() => {this.handleOpen('Deposit')}} />
          </CardActions>      
        </div>
      );
    }
  }
}

class Stake extends Component {

  constructor(props) {
    super(props);
    this.state = {
      "dialogOpen": false,
      "dialogTitle": "Deposit Amount",
      "amount": 0,
      "password": ""
    }
  }

  handleOpen = (title) => {
    this.setState({dialogOpen: true, dialogTitle: title});
  };

  handleClose = () => {
    this.setState({dialogOpen: false});
  };

  onAmountChange = (e) => {
    this.setState({amount: e.target.value});
  };

  onPasswordChange = (e) => {
    this.setState({password: e.target.value});
  }

  checkPowerStatus = () => {
    this.props.notify('There will be a summary here!', 'success')
  }

  stakeAction = () => {
    let password = this.state.password;
    let amount = this.state.amount;
    let data = new FormData();
    let address = "";
    if(this.state.dialogTitle === 'Deposit') {
      address = "/deposit";  
    }
    else{
      address = "/withdraw";
    }
    
    data.append('amount', amount);
    data.append('password', password);

    axios.post(address, data).then((response) => {
      let success = response.data.success;
      if(success) {
        this.props.notify(response.data.message, 'success');
      }
      else {
        this.props.notify(response.data.message, 'error');
      }
    })

    this.setState({dialogOpen: false, amount:0, password:""});
  }

  render() {
    let score = 0;
    let applicationMode = 'Single';
    let applicationList = [];
    let name = "";
    let assignedJob = "None";
    if(this.props.account !== null){
      score = this.props.account.score;
      applicationMode = this.props.account.application.mode == 's' ? 'Single':'Continous';
      applicationList = this.props.account.application.list;
      name = this.props.wallet.name;
      if(this.props.account.assigned_job.auth !== null) {
        assignedJob = "Auth " + this.props.wallet.assigned_job.auth + " JobId " + this.props.wallet.assigned_job.job_id;
      }
    }

    const actions = [
      <RaisedButton
        label="Ok"
        primary={true}
        keyboardFocused={true}
        onClick={this.stakeAction}
      />,
    ];

    return (
      <Card style={{width:"100%"}}>
        <CardHeader
          title="Summary"
          subtitle="Power information about your wallet on Blockchain"
          actAsExpander={true}
          showExpandableButton={true}
        />
        <CardText expandable={true}>
          You can find valuable information about your wallet's Power details that is registered on Blockchain.
        </CardText>
        <CardText>
          <Table selectable={false}>
            <TableBody displayRowCheckbox={false}>
              <TableRow>
                <TableHeaderColumn>Score</TableHeaderColumn>
                <TableHeaderColumn>{score}</TableHeaderColumn>
              </TableRow>
              <TableRow>
                <TableHeaderColumn>Assigned Job</TableHeaderColumn>
                <TableHeaderColumn>{assignedJob}</TableHeaderColumn>
              </TableRow>
              <TableRow>
                <TableHeaderColumn>Application Mode</TableHeaderColumn>
                <TableHeaderColumn>{applicationMode}</TableHeaderColumn>
              </TableRow>
              <TableRow>
                <TableHeaderColumn>Application List</TableHeaderColumn>
                <TableHeaderColumn>{applicationList.join(", ")}</TableHeaderColumn>
              </TableRow>
            </TableBody>
          </Table>
        </CardText>
        <RequiredActionPower account={this.props.account} />
        <Dialog
          title={this.state.dialogTitle}
          actions={actions}
          modal={false}
          open={this.state.dialogOpen}
          onRequestClose={this.handleClose}
        >
          <TextField
              fullWidth={true}
              floatingLabelText="Amount"
              name="amount"
              type="text"
              onChange={this.onAmountChange}
            />
         <TextField
              fullWidth={true}
              floatingLabelText="Password"
              name="password"
              type="password"
              onChange={this.onPasswordChange}
            />
        </Dialog>
      </Card>
    );
  }
}

export default Stake;