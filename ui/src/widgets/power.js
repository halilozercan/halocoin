import React, { Component } from 'react';
import {MCardStats} from '../components/card.js';
import axios from 'axios';
import LinearProgress from 'material-ui/LinearProgress';
import {Card, CardActions, CardHeader, CardMedia, CardTitle, CardText} from 'material-ui/Card';
import Avatar from 'material-ui/Avatar';
import FlatButton from 'material-ui/FlatButton';
import FontIcon from 'material-ui/FontIcon';
import {red500, green500} from 'material-ui/styles/colors';

class Power extends Component {
  constructor(props) {
    super(props);
    this.state = {
      'status': 'Loading...',
      'description': '',
      'running': false
    }
    this.props.socket.on('power_status', (data) => {
      this.setState((state) => {
        state['running'] = data.running;
        state['status'] = data.status;
        state['description'] = data.description;
        return state;
      });
    });
  }

  componentWillMount() {
    this.update();
  }

  update() {
    /*
    axios.get('/docker').then((response) => {
      if(response.data.success) {
        this.setState({
          available: 'Power service is ready!'
        })
      }
      else{
        this.setState({
          available: 'Power service is currently unavailable'
        })
      }
    }).catch((error) => {
      this.setState({
        available: 'Power service is currently unavailable'
      })
    });
    */
    axios.get("/power").then((response) => {
      let data = response.data;
      this.setState((state) => {
        state['running'] = data.running;
        state['status'] = data.status;
        state['description'] = data.description;
        return state;
      });
    });
  }

  render() {
    return (
      <Card>
        <CardHeader
          title="Power Status"
          subtitle={this.state.description}
          avatar={<Avatar backgroundColor={this.state.running ? green500:red500} 
                  icon={<FontIcon className="material-icons">whatshot</FontIcon>} />}
        />
        <CardActions style={{ width: '100%', textAlign: 'right' }}>
          <FlatButton onClick={() => {console.log(this.state.description);}} label={this.state.status} disabled={this.state.description == ''}/>
        </CardActions>
      </Card>
    );
  }
}

export default Power;