import React, { Component } from 'react';
import {MCardStats} from '../components/card.js';
import {Card, CardActions, CardHeader, CardText} from 'material-ui/Card';
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
        this.props.notify('Successfully updated your default wallet', 'success');
      }
      else {
        this.props.notify('Failed to update your default wallet', 'error');
      }
    })

    this.setState({dialogOpen: false, amount:0, password:""});
  }

  render() {
    let balance = 0;
    let deposit = 0;
    let name = "";
    let job_assignment = "None";
    if(this.props.wallet !== null){
      deposit = this.props.wallet.deposit;
      balance = this.props.wallet.balance;
      name = this.props.wallet.name;
      if(this.props.wallet.assigned_job !== '') {
        job_assignment = this.props.wallet.assigned_job;
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
      <div className="col-lg-6 col-md-12 col-sm-12">
        <Card style={{width:"100%"}}>
          <CardHeader
            title="Stake in Pool"
            subtitle="Amount of coins you deposited as your stake"
            actAsExpander={true}
            showExpandableButton={true}
          />
          <CardText expandable={true}>
            Tasks inside Coinami project are distributed according to stakes of each wallet.
            More information is available on Coinami web page. You need to be very careful about
            your deposit amount. When a job is assigned to an address, half of reward is taken from
            the stake of that address. 
            To make sure your system is ready to work on jobs, click <a href="#" onClick={this.checkPowerStatus}>here</a> and get your result
          </CardText>
          <CardText>
            <Table selectable={false}>
              <TableHeader  displaySelectAll={false} adjustForCheckbox={false}>
                <TableRow selectable={false}>
                  <TableHeaderColumn style={{fontWeight:"bold"}}>Balance</TableHeaderColumn>
                  <TableHeaderColumn style={{fontWeight:"bold"}}>Stake</TableHeaderColumn>
                  <TableHeaderColumn style={{fontWeight:"bold"}}>Job Assignment</TableHeaderColumn>
                </TableRow>
              </TableHeader>
              <TableBody displayRowCheckbox={false}>
                <TableRow>
                  <TableHeaderColumn><a>{balance}</a></TableHeaderColumn>
                  <TableHeaderColumn><a>{deposit}</a></TableHeaderColumn>
                  <TableHeaderColumn><a>{job_assignment}</a></TableHeaderColumn>
                </TableRow>
              </TableBody>
            </Table>
          </CardText>
          <CardActions align='right'>
            <RaisedButton label="Deposit" primary={true} onClick={() => {this.handleOpen('Deposit')}} />
            <RaisedButton label="Withdraw" secondary={true} onClick={() => {this.handleOpen('Withdraw')}} />
          </CardActions>
        </Card>
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
      </div>

    );
  }
}

export default Stake;